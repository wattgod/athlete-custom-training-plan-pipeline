# Improvement backlog — 2026-06-28

**Quality 3.07** · avg coach 6.38/10 · contract pass 62% · load 8.88/plan · 6 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/time_crunched_parent)
> Discipline mismatch in content framing: Birkebeinerrittet Sykkel is a famous Norwegian mountain/gravel sportive with significant climbing (Rena to Lillehammer crosses the Birkebeiner mountain pass). The guide is framed as a pure road plan with road-specific skills sections and no mention of climbing strategy, descending on rough terrain, or the sustained high-power demands of mountain passes. For a 48-year-old targeting a finish on this specific course, the omission of climbing-specific preparation (sustained threshold climbing, gear selection for long gradients) is a meaningful gap that could embarrass the business if the athlete arrives unprepared for the terrain.

### 2. [critical] ×1  (gravel/masters_returner)
> Off-day list is internally contradictory and wrong: the guide states 'Off days: Wednesday, Tuesday, Thursday' — that is THREE off days listed in a jumbled, non-chronological order (Tuesday, Wednesday, Thursday) for a plan that targets 4 training days/week. An athlete with 8 h/week on a 7-day schedule needs only 3 off days, but listing Tuesday AND Thursday AND Wednesday as off days leaves only Mon/Fri/Sat/Sun as ride days, which is plausible, yet the ordering (Wed, Tue, Thu) reads as a generation artifact and will confuse the athlete. The off-day list must be stated clearly and in day-order.

### 3. [critical] ×1  (gravel/masters_returner)
> Weekly Volume preview check flagged WARN but no explanation or mitigation is provided anywhere in the guide text. A WARN on volume for a masters returner (the highest-risk persona for overreaching) must be explicitly acknowledged — either the volume is adjusted, or the guide must contain a clear coach note explaining why the prescribed volume is appropriate despite the flag. Sending a plan with a silent volume warning to a 56-year-old returning athlete is a liability.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch throughout the guide. The athlete's discipline is MTB, but the plan repeatedly uses gravel-specific language: the race is called 'Trough Creek Gravel Grinder' (correct per the DB), there is a dedicated 'Gravel Skills' section listed in the table of contents, and the framing of outdoor rides references 'gravel' conditions. A separate MTB-specific skills section (e.g. technical descending, trail braking, switchbacks, body position) should replace or supplement the gravel content. Sending a gravel-focused guide to an MTB racer is embarrassing and potentially harmful to race preparation.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> FTP value displayed as body weight. The athlete profile card reads '123 lbs Weight (55.8 kg)' — but 123 is actually the athlete's FTP in watts; no body weight was provided in the athlete data. The plan has incorrectly injected the FTP figure into the weight field. This is factually wrong, potentially confusing, and undermines trust in the plan's accuracy.

### 6. [critical] ×1  (gravel/ambitious_first_timer)
> Weight (169 lbs / 76.6 kg) and height (5'8") appear in the athlete profile section but are NOT present in the plan JSON — the athlete never supplied this data. These numbers were hallucinated or pulled from a default template. Sending fabricated biometric data to a paying customer is a trust-destroying error and must be removed or replaced with a placeholder.

### 7. [major] ×1  (gravel/masters_returner)
> Off-days are listed as 'Tuesday, Wednesday, Monday' — three days listed in a non-chronological, confusing order that implies only 4 training days, which is correct for 9 h/week, but naming Monday as a third off day alongside Tuesday AND Wednesday means three consecutive off days mid-week and start-of-week, which would be an unusual and potentially problematic structure. The ordering (Tue, Wed, Mon) is also incoherent — Monday comes after Wednesday in the list, suggesting a copy/paste or generation error. This needs to be verified against the calendar and corrected.

### 8. [major] ×1  (gravel/masters_returner)
> Preview check flags 'Zone Distribution: FAIL' — the guide text is not available in full so it cannot be confirmed the calendar corrects this, but a failing zone distribution check means athletes may be prescribed too much time in Zone 3 (the gray zone the guide itself explicitly warns against). This contradiction between the methodology prose and the actual scheduled zone distribution is a credibility risk if not resolved in the calendar.

### 9. [major] ×1  (road/time_crunched_parent)
> Zone Distribution preview check is a hard FAIL, yet the guide text contains no acknowledgment or explanation. The methodology claims ~70% Zone 2 in the plan, but the automated check flagged the actual distribution as non-compliant. Sending a guide that asserts correct zone distribution without reconciling a known failure is misleading to the athlete.

### 10. [major] ×1  (road/time_crunched_parent)
> Two preview warnings (TSS Progression and Taper Intensity) are unresolved. TSS Progression WARN could indicate a load spike or insufficient ramp; Taper Intensity WARN could mean intensity is not being adequately maintained during taper. Neither is addressed in the guide, meaning the athlete receives no coaching context for what may be structural weaknesses in the plan.

### 11. [major] ×1  (gravel/masters_returner)
> The 'Road Skills' section is listed in the Table of Contents. This is a gravel event (5 Mila Marche Gran Fondo) held on mixed terrain in the Marche hills. Road skills content (e.g., road cornering, peloton riding, criterium tactics) would be wrong for this discipline; the section should cover gravel-specific skills: loose-surface cornering, descending on gravel, tire-pressure management, and navigation. The section text is truncated so the actual content cannot be verified, but the heading alone is a red flag that must be checked and corrected.

### 12. [major] ×1  (mtb/ambitious_first_timer)
> Race name vs. discipline conflict creates an internal inconsistency. The race in the verified DB is 'Trough Creek Gravel Grinder' yet the athlete's discipline is MTB. The guide never addresses this tension. A real coach would flag it — either the athlete is doing a gravel event on an MTB (requiring a note) or the event categorization needs clarification. Silently generating an MTB plan for a race explicitly called a 'Gravel Grinder' is confusing and may reflect a data error that should be surfaced to the athlete.

### 13. [major] ×1  (mtb/ambitious_first_timer)
> Height field ('5'4"') has no source in the athlete data JSON. No height was provided, so this value appears to have been fabricated or hallucinated by the generator. Invented athlete profile data should never appear in a sent plan.

### 14. [major] ×1  (gravel/ambitious_first_timer)
> Zone 1 upper boundary is listed as 110W (55% FTP) but the standard cutoff for a 200W FTP athlete is ~110W (55%), while Zone 2 starts at 111W — that part is fine. However, Zone 4 Threshold is shown as 187–210W (94–105% FTP) yet the GS zone tops out at 186W (93% FTP), leaving no gap. The real inconsistency is the Zone 4 ceiling of 210W = 105% FTP, which overlaps into VO2max territory for this methodology. This should be 100% FTP (200W) as the ceiling, with VO2max starting at 201W — as written it could cause an athlete to do VO2max-level work while thinking they're in threshold.

### 15. [major] ×1  (gravel/ambitious_first_timer)
> The guide states 'The test result sets ALL your training zones for the next 6 weeks' in the FTP test warning box, but the plan is only 8 weeks long and schedules tests per the FTP Test Frequency check. This boilerplate text is misleading in an 8-week context and should be updated to reflect the actual plan length.

### 16. [major] ×1  (gravel/weekend_warrior)
> Long-ride duration claim is internally contradictory and undersells the problem. The guide states peak long rides are '1.5–2 hours' but also says 'A single 3-4 hour ride is worth more than two 1.5 hour rides.' For a 78.84-mile gravel race with an estimated ~4.9 h finish time (per fueling data), a 2-hour long ride is only ~41% of race duration — well below the 60–70% minimum threshold most coaches target. The plan needs to either build the athlete toward at least one 3+ hour ride or state explicitly and upfront that this is a structural limitation of the 4 h/week budget, not just an 'opportunity.' As written, the contradiction could confuse the athlete about what is actually planned vs. aspirational.

### 17. [major] ×1  (gravel/weekend_warrior)
> The Weekly Volume automated check flagged WARN but the guide body never explicitly addresses what the weekly hours actually look like across the 13 weeks. A paying customer reading this guide cannot reconcile the WARN without context. A brief sentence (e.g., 'Some weeks will peak at ~5 h to accommodate a longer ride; most will sit at 3.5–4 h') is needed to close that gap.

### 18. [minor] ×1  (gravel/masters_returner)
> The guide states the FTP test result 'sets ALL your training zones for the next 6 weeks' — but this is a 10-week plan with a single retest cadence implied. Saying '6 weeks' is an oddly specific and potentially inaccurate timeframe that could confuse the athlete if zones are updated mid-plan at a different interval.

### 19. [minor] ×1  (gravel/masters_returner)
> The '22 Years Riding' shown in the profile is plausible but was not present in the athlete JSON provided — if this was inferred or hallucinated rather than pulled from questionnaire data, it is an unverifiable claim that could be wrong and embarrassing.

### 20. [minor] ×1  (road/time_crunched_parent)
> The weekly structure states off days are Tuesday, Saturday, and Sunday, giving only 4 training days — yet Saturday and Sunday off is unusual for a time-crunched athlete who typically needs the weekend long ride. If Saturday or Sunday is truly off, the long ride anchor (listed as Thursday) is the only weekend-adjacent session, which compresses recovery and may partly explain the TSS Progression warning.

### 21. [minor] ×1  (road/time_crunched_parent)
> The guide mentions 'Strength training: Included (home gym)' in the at-a-glance block, but the truncated text contains only generic strength advice (single-leg, core, hip). For a masters athlete (48) with a mountain sportive target, no specificity around eccentric quad loading or climbing-specific strength is a missed opportunity and slightly inconsistent with the personalization promise.

### 22. [minor] ×1  (mtb/ambitious_first_timer)
> The '2 Years Riding' experience label appears in the profile card but the source JSON does not include a years_riding or experience field. If this was inferred from the persona label ('ambitious_first_timer'), calling it '2 Years Riding / Intermediate level' in the methodology section may misrepresent the athlete's background and should be verified or removed.

### 23. [minor] ×1  (mtb/ambitious_first_timer)
> The long ride duration range cited ('1.6-2.8 hours') seems low relative to the fueling data (4.2 h expected race duration) and the plan's own advice that a single 3-4 hour ride is highly valuable. The guide contradicts itself by advising longer rides while capping the stated peak long-ride range well below race duration.

### 24. [minor] ×1  (gravel/ambitious_first_timer)
> TSS Progression flagged WARN in the preview checks, but the guide contains no acknowledgment or coaching note about the non-standard progression. A brief callout (e.g., 'Week X is intentionally compressed — here's why') would prevent athlete confusion and is standard practice for a plan with a flagged check.

### 25. [minor] ×1  (gravel/ambitious_first_timer)
> The 'Years Riding: 3' data point appears in the profile and is referenced in the methodology rationale, but the plan JSON does not contain a years_riding field — this value should be verified as athlete-supplied rather than assumed from the persona label.
