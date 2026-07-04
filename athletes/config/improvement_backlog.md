# Improvement backlog — 2026-07-04

**Quality 5.46** · avg coach 7.5/10 · contract pass 88% · load 7.0/plan · 2 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/veteran_podium_chaser)
> Automated Weekly Volume check FAILED and is unresolved. The guide claims 15 h/week throughout, but the preview gate flagged this. Before sending, the actual weekly hour totals in the calendar must be audited to confirm they do not exceed or significantly undercut the 15 h target — especially critical for a veteran athlete whose overtraining risk at high volume is real. Sending a guide whose own QA gate says the volume is wrong is not acceptable.

### 2. [critical] ×1  (road/weekend_warrior)
> The guide states 'your peak duration of 1.5 hours' as the long ride ceiling. For a 78.3-mile gran fondo estimated at ~4.9 hours of race time, a 1.5-hour peak long ride is grossly inadequate and directly contradicts the fueling section's 4.9-hour duration assumption. This number will alarm any attentive athlete and undermines confidence in the plan. The guide even warns the athlete that longer rides are needed — yet simultaneously caps the long ride at 1.5 hours. These two statements cannot coexist. The long ride peak duration must be corrected to something credible given the 5 hr/week budget (e.g., 2.5–3.5 hours on a big Saturday) before sending.

### 3. [major] ×1  (road/masters_returner)
> The zone chart is missing explicit watt ranges for Zone 1 (Active Recovery shows '0-90W' but Zones 2, 5, and 6 show no watt values — only % FTP is listed). For a rider with a known FTP of 165 W, absolute watt targets should be filled in for every zone so the athlete can program their head unit without doing manual math. This is a usability gap that could lead to wrong-zone training.

### 4. [major] ×1  (road/masters_returner)
> The plan describes the athlete as 'Intermediate level' in the methodology rationale section, but the persona is 'masters_returner' — a returning athlete after a layoff. Calling a returner 'Intermediate' without qualification misrepresents their current fitness state and could cause the athlete to push harder than appropriate in early base weeks.

### 5. [major] ×1  (gravel/time_crunched_parent)
> Off-day conflict with long-ride day: The plan states off days are Monday, Saturday, AND Sunday, yet the long ride is placed on Friday. That gives this athlete only 4 training days (Tue/Wed/Thu/Fri) to accumulate 7 hours/week with a long ride capped to Friday. With Saturday listed as a full rest day, the athlete loses the most common long-ride slot for a time-crunched parent; more critically, the plan must be internally consistent — if Saturday is truly an off day, the guide should not elsewhere imply weekend riding is available, and the weekly structure section should explicitly acknowledge this unusual layout to avoid athlete confusion.

### 6. [major] ×1  (gravel/time_crunched_parent)
> Off-days listed as 'Thursday, Wednesday, Saturday' — that is three off days in a single week, leaving only four riding days, which is plausible for 8 h/week, but the ordering (Thursday listed before Wednesday) reads oddly and may indicate a copy-paste error or day-order scramble. If the intended off days are Wednesday, Thursday, Saturday, the text should say so in calendar order. Worth verifying against the actual calendar before sending, as a mismatch between this summary and the calendar would confuse the athlete.

### 7. [minor] ×2  (gravel/ambitious_first_timer, gravel/time_crunched_parent)
> FTP Test Frequency flagged WARN in the preview checks, but the guide text states 'The test result sets ALL your training zones for the next 6 weeks' — implying a single test covers the entire 10-week plan. For a 10-week plan, a mid-plan retest around week 5-6 is standard practice and should be referenced here to reassure the athlete their zones stay accurate; the current wording may cause them to ignore a scheduled mid-plan test.

### 8. [major] ×1  (gravel/ambitious_first_timer)
> Zone chart is missing the % FTP column values for Zones 1 and 6. Zone 1 shows '0-129W' but no '% FTP' label (should be '<55% FTP'), and Zone 6 shows '>283W / >120% FTP' but the '%FTP' cell appears blank in the table rendering. An athlete relying on a different FTP after a retest will have no percentage anchor for these zones.

### 9. [minor] ×2  (gravel/ambitious_first_timer, road/time_crunched_parent)
> The athlete's weight (181 lbs / 82.1 kg) and height (5'8") appear in the profile section but were not present in the plan JSON — these values cannot be verified against source data provided, meaning they may have been hallucinated or pulled from a stale profile. If incorrect, the post-ride nutrition numbers (anchored to 82 kg) would also be wrong.

### 10. [major] ×1  (road/veteran_podium_chaser)
> The Weekly Volume automated check returned WARN but no explanation or mitigation is surfaced in the guide. At 14 h/week for a 9-week plan, volume may be ambitious or the checker flagged a specific week; either way, the guide should either justify the load or flag it to the athlete. Sending without addressing this risks delivering a plan with an overload week we haven't explained.

### 11. [major] ×1  (road/veteran_podium_chaser)
> The off-day listing reads 'Off days: Tuesday, Monday' — listing Tuesday before Monday is confusing and likely a template/sort error. For a road-racing athlete planning their week, this reads as unprofessional and could cause scheduling confusion.

### 12. [major] ×1  (road/veteran_podium_chaser)
> Experience level is contradicted: the guide body says '16 years of cycling experience at Intermediate level', but a rider with 16 years of experience chasing a podium at an A-priority granfondo is almost certainly Advanced/Expert. Labelling her 'Intermediate' undermines credibility with a paying athlete of this calibre and could cause the plan's stated rationale ('matched to your experience level') to ring false.

### 13. [major] ×1  (road/veteran_podium_chaser)
> Zone 2 lower-bound power is missing from the zone chart. Zone 2 shows '122-165 W' but the %FTP column entry reads '56-75% FTP' with no lower bound listed (the cell for Zone 1 %FTP is also blank). A power-meter user needs the complete range for every zone; missing values in the reference chart the athlete uses every ride is a meaningful error.

### 14. [major] ×1  (road/time_crunched_parent)
> The guide states 'The test result sets ALL your training zones for the next 6 weeks' but the plan JSON shows FTP tests are passing the FTP Test Frequency check for a 19-week plan — a 6-week validity window implies roughly 3 tests, which may not align with the actual scheduled test count visible in the calendar. If the calendar only schedules 2 tests, this claim will leave the athlete with unguided zones for the final stretch. This should be reconciled with the actual calendar before sending.

### 15. [major] ×1  (road/time_crunched_parent)
> The Recovery Protocol section ends mid-sentence ('Next day should be') — the text is truncated and the guide as submitted is incomplete. A paying customer receiving a PDF with a cut-off sentence is embarrassing and unprofessional, regardless of whether it is a truncation artifact in the QA submission.

### 16. [major] ×1  (road/weekend_warrior)
> The Zone chart omits power percentages for Zone 1 (Active Recovery) — the upper boundary shows '0-107W' but no %FTP column entry is given, while all other zones show a %FTP range. Minor inconsistency, but a paying athlete who tries to back-calculate will notice the missing column value and may lose trust in the chart.

### 17. [minor] ×1  (road/masters_returner)
> The countdown states '92 days from today' which is a dynamic value that should have been resolved to a static date-relative statement at generation time. If the PDF is opened weeks later, the countdown will appear wrong and erode trust in the document's accuracy.

### 18. [minor] ×1  (road/masters_returner)
> The long ride duration range cited in the Weekly Structure section ('2.1-3.5 hours') should be cross-checked against the 7 h/week budget and the Per-Day Duration Caps pass — while the automated gate passed this, the upper end of 3.5 hours for a 7 h/week athlete consumes 50% of weekly volume in a single ride, which warrants a coach's eye to confirm it only appears in peak weeks, not base weeks.

### 19. [minor] ×1  (gravel/time_crunched_parent)
> Fueling section references 70g/hr carbs and a 6.8h race duration in the JSON, but the truncated guide text only surfaces a post-ride recovery window (32g protein, 79-95g carbs) without showing the on-bike fueling guidance. If the race-day and long-ride fueling section (70g/hr × 6.8h ≈ 476g carbs total) is absent or buried, the athlete is missing critical gravel-specific nutrition detail for a ~7-hour effort.

### 20. [minor] ×1  (gravel/time_crunched_parent)
> Weight listed in the profile block as '174 lbs / 78.9 kg' — this is consistent (174 lbs ÷ 2.205 = 78.9 kg) and matches the post-ride nutrition calc, but the weight was not present in the supplied athlete JSON, meaning it was either drawn from the questionnaire or generated. If generated/assumed, it must be confirmed against the athlete's actual questionnaire response before sending to avoid an embarrassing mismatch.

### 21. [minor] ×1  (gravel/time_crunched_parent)
> Long ride duration range cited as '3–5.1 hours' in the Weekly Structure section. The 5.1-hour upper bound is oddly precise (presumably auto-generated) and will look strange to the athlete — rounding to '3–5 hours' or 'up to 5 hours' would read more naturally and professionally.

### 22. [minor] ×1  (gravel/ambitious_first_timer)
> The 'YOUR WEEK, AT A GLANCE' section lists off days as 'Friday, Wednesday' — this ordering is slightly confusing (non-chronological) and could cause a reader to misread their weekly structure. Should read 'Wednesday, Friday' to follow calendar order.

### 23. [minor] ×1  (road/veteran_podium_chaser)
> The Zone 1 row in the zone chart is missing % FTP and % LTHR columns (shown as blank). While Zone 1 is loosely defined by convention, the inconsistency with every other row looks like a template rendering gap and may confuse a data-oriented athlete.

### 24. [minor] ×1  (road/veteran_podium_chaser)
> The plan describes 5 training days with '2 key sessions,' but the long ride is separately called the 'backbone' and appears to be a third distinct session type. The math (5 days, 2 key, plus long ride, easy rides, and strength) is never fully reconciled in the weekly structure section, which could leave the athlete uncertain about how many hard days they actually have.

### 25. [minor] ×1  (road/veteran_podium_chaser)
> 'GS G Spot' zone label (between Tempo and Threshold) is non-standard and will likely strike many athletes as odd or unprofessional, especially in a paid plan. Consider renaming to 'Sweet Spot' or 'Sub-Threshold' for credibility.
