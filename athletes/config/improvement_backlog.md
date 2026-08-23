# Improvement backlog — 2026-08-23

**Quality -0.37** · avg coach 5.38/10 · contract pass 50% · load 14.38/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/time_crunched_parent)
> Off-days listed as 'Thursday, Saturday, Friday' — three days off in a 5h/week plan is internally contradictory, and listing Saturday as an off-day directly conflicts with the long-ride day being Sunday (a 5h athlete needs Saturday as a prep or ride day). Three off-days also leaves only 4 training days, which is borderline workable but the Saturday off is the specific problem given Sunday long rides.

### 2. [critical] ×1  (gravel/time_crunched_parent)
> Table of contents and guide body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — this is a gravel event plan, not a road criterium/road race plan. These sections are discipline-wrong and will confuse or embarrass the athlete.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> The table of contents and a dedicated section include 'Category 5 to Category 1 Pathway' — this is a USA Cycling road racing licensing ladder section that has zero relevance to a UCI Gran Fondo and is actively misleading for a 16-year veteran podium chaser. It must be removed entirely.

### 4. [critical] ×1  (road/veteran_podium_chaser)
> The guide describes the athlete's experience as 'Intermediate level' despite the athlete data showing 16 years of riding experience. This directly contradicts the athlete's profile and will erode trust immediately. A 16-year rider targeting a podium must be labeled Advanced or Experienced racer.

### 5. [critical] ×1  (gravel/veteran_podium_chaser)
> Zone Distribution check is flagged FAIL in the preview checks, yet the guide text presents the distribution as correctly set (~65% easy). The guide should not be sent until the underlying zone distribution issue is understood and resolved — if the calendar has too much Z3/Z4 relative to the stated ~65% easy target, the guide's prose promise contradicts what the athlete will actually do.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> Wrong discipline content included: 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents for a GRAVEL athlete. Road racing categories and road race tactics are irrelevant and potentially misleading for a Gran Fondo gravel event — this is the exact cross-discipline contamination the QA process exists to catch.

### 7. [critical] ×1  (gravel/time_crunched_parent)
> Goal mismatch — athlete's goal is 'podium' but the guide's success metric is listed only as 'Compete.' A podium goal requires explicit race-specific intensity targets, competitive pacing strategy, and performance benchmarks. Reducing it to 'Compete' misrepresents the athlete's stated objective and undermines the plan's credibility.

### 8. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections are listed in the Table of Contents — these are road racing / criterium concepts that are completely wrong for a gravel event. Sending a gravel athlete a Cat 5-to-Cat 1 upgrade pathway is embarrassing and undermines coaching credibility.

### 9. [critical] ×1  (gravel/masters_returner)
> Athlete weight is stated as '151 lbs (68.5 kg)' but no weight was provided in the athlete data JSON. This is a fabricated number inserted into the guide — a serious data-accuracy failure that erodes trust if the athlete notices it does not match reality.

### 10. [critical] ×1  (gravel/masters_returner)
> Per-Day Duration Cap check is flagged FAIL in the preview checks, meaning at least one day's prescribed ride exceeds the allowed ceiling for this athlete. This must be resolved before sending — an over-long day for a 50-year-old masters returner risks injury or dropout.

### 11. [critical] ×1  (gravel/ambitious_first_timer)
> Preview check flagged Per-Day Duration Caps as FAIL. The guide text references long rides of '4–6.8 hours' for an athlete on an 11 h/week budget. A 6.8-hour single ride would consume 62% of the weekly hour budget in one session, leaving almost no room for any other training day. This contradicts reasonable per-day caps and could produce dangerous overload or make the rest of the week's structure impossible. The specific day(s) breaching the cap must be corrected before sending.

### 12. [major] ×1  (gravel/time_crunched_parent)
> The off-day string 'Thursday, Saturday, Friday' lists days out of calendar order (Thu, Sat, Fri) which reads as a data rendering bug — days should appear in weekly order (e.g. Thursday, Friday, Saturday) and the combination itself needs re-evaluation against the athlete's actual stated availability.

### 13. [major] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section in the ToC is ambiguous but acceptable only if it covers gravel-specific skills (loose surface cornering, tire pressure, trail braking). If it mirrors road-racing content, it is wrong for this discipline — cannot confirm from truncated text but the surrounding 'Road Race Strategy' context makes this suspicious.

### 14. [major] ×1  (road/veteran_podium_chaser)
> The automated preview flags a Per-Day Duration Cap FAIL, meaning at least one day in the calendar exceeds the expected cap for an 11 h/week plan. The guide text does not acknowledge or correct this, so the calendar could contain an illegal session that risks overtraining or injury.

### 15. [major] ×1  (road/veteran_podium_chaser)
> Weekly Volume and TSS Progression are both flagged WARN by the preview. The guide makes no mention of any intentional deviation or rationale, which means the athlete receives a plan with potentially erratic volume or TSS without explanation — a red flag for a paying customer expecting a coherent periodized plan.

### 16. [major] ×1  (gravel/veteran_podium_chaser)
> Sunday is listed as an off day ('Off days: Sunday, Monday'), but the race (Gravelista) falls on Sunday, October 25. This creates a direct contradiction: the athlete's race day is coded as a rest day. The taper week calendar almost certainly handles this, but the guide text states it explicitly and will confuse or alarm the athlete.

### 17. [major] ×1  (gravel/veteran_podium_chaser)
> FTP test section states 'The test result sets ALL your training zones for the next 6 weeks' — but this is a 9-week plan. The '6 weeks' figure is generic boilerplate that directly contradicts the plan length and will undermine athlete confidence in the document's accuracy.

### 18. [minor] ×2  (gravel/masters_returner, gravel/veteran_podium_chaser)
> Long ride duration range cited as '3.7–6.2 hours' in the Weekly Structure section — the upper bound of 6.2 hours would significantly exceed the athlete's 10 h/week target when combined with other sessions, and should be verified against the actual calendar caps (Per-Day Duration Caps passed, so this may simply be imprecise prose).

### 19. [major] ×1  (gravel/veteran_podium_chaser)
> Height listed as 5'6" but weight shown as 158 lbs (71.7 kg) — neither figure appears in the provided athlete JSON (only age 40, FTP 260, hours 11 are supplied). These numbers are either fabricated or pulled from a wrong athlete profile. Sending fabricated biometric data to a paying athlete is embarrassing and erodes trust.

### 20. [major] ×1  (gravel/veteran_podium_chaser)
> Three automated preview checks flagged WARN (TSS Progression, FTP Test Frequency, Taper Intensity) and none are addressed or explained in the guide text. A head coach must either confirm they are acceptable edge cases or fix the underlying plan before sending — they cannot simply be ignored.

### 21. [major] ×1  (gravel/time_crunched_parent)
> Long ride duration is flagged internally as only 1.5 hours for a 78-mile (~4-hour) race, yet no corrective action is taken in the plan structure — just a sidebar note. For a podium-seeking athlete the plan should enforce at least one or two longer ride exceptions; the warn-and-move-on approach is insufficient.

### 22. [major] ×1  (gravel/time_crunched_parent)
> TSS Progression and Taper Intensity both flagged WARN in preview checks but neither issue is addressed or acknowledged in the guide text. A TSS ramp-rate problem and a taper intensity problem are coaching errors, not formatting errors — they must be resolved before sending.

### 23. [major] ×1  (gravel/time_crunched_parent)
> The guide mentions 'Road Skills' as a dedicated section in the table of contents. For a gravel gran fondo, this section should cover gravel-specific skills (loose surface cornering, descending on gravel, tire pressure management, rough terrain pacing) — 'Road Skills' framing signals the wrong content is present.

### 24. [major] ×1  (gravel/masters_returner)
> Weekly Volume check is WARN and FTP Test Frequency check is WARN — neither is explained or acknowledged anywhere in the guide text. A coach would at minimum note why volume is flagged (e.g., a specific week is above target) or justify the FTP test cadence for a 9-week plan.

### 25. [major] ×1  (gravel/masters_returner)
> Off days are listed as 'Saturday, Friday, Tuesday' — three off days in a 9-hour/week plan means only four riding days, which is plausible, but having both Friday and Saturday off while Sunday is the long ride day is an unusual structure that is never explained. More importantly, listing off days before ride days in the 'at a glance' block reads oddly and will confuse the athlete.
