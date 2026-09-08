# Improvement backlog — 2026-09-08

**Quality 1.38** · avg coach 5.62/10 · contract pass 88% · load 12.5/plan · 10 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/time_crunched_parent)
> Off-day list is contradictory and almost certainly wrong: 'Off days: Wednesday, Saturday, Tuesday' lists THREE off days. The athlete targets 8 h/week with 4 training days, implying 3 off days — but listing Tuesday AND Saturday as off days alongside Wednesday is suspicious. More importantly, Saturday is a prime long-ride day for a time-crunched parent; if Saturday is truly an off day that needs to be confirmed against the calendar, the guide text as written will confuse or mislead the athlete.

### 2. [critical] ×1  (gravel/time_crunched_parent)
> The guide contains sections titled 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' — this is a GRAVEL plan. Those sections are copied from a road-racing template and are wrong for the discipline. A gravel athlete does not race in USA Cycling road categories, and road crit/peloton tactics are irrelevant or actively harmful advice for a gran fondo.

### 3. [critical] ×1  (road/weekend_warrior)
> The guide includes a 'Category 5 to Category 1 Pathway' section. This athlete is a 41-year-old weekend warrior whose goal is simply to finish a gran fondo — UCI gran fondos do not use USA Cycling cat licensing, and even if they did, a finish-goal rider has zero use for a cat upgrade pathway. This content is from the wrong template and will confuse or embarrass the business in front of a paying customer.

### 4. [critical] ×1  (gravel/ambitious_first_timer)
> Road Race Strategy and 'Category 5 to Category 1 Pathway' sections appear in the table of contents and (implied) body of a GRAVEL plan. These are road-racing constructs (Cat 5–1 licensing is a USA Cycling road/crit category system) and are completely wrong for a gravel event. This is the most embarrassing content error — a paying gravel athlete receiving a road-racing career ladder.

### 5. [critical] ×1  (gravel/ambitious_first_timer)
> Taper Intensity is flagged WARN in the automated preview checks, meaning the taper week intensity is not properly controlled. This is a plan-integrity issue: sending a plan with a known unresolved taper problem risks the athlete arriving at their A-race fatigued rather than fresh.

### 6. [critical] ×1  (road/time_crunched_parent)
> Discipline mismatch — the Contents list includes 'Road Skills', 'Road Race Strategy', AND a 'Category 5 to Category 1 Pathway' section. A Cat 5→Cat 1 racing progression pathway is entirely irrelevant to an athlete whose goal is simply to finish a 71-mile gran fondo. This content belongs in a criterium/road-race upgrade plan, not a gran fondo completion plan, and will confuse or mislead the athlete.

### 7. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section is included in the table of contents and (presumably) the body. This athlete's goal is simply to FINISH a 68-mile gran fondo — a Cat 5-to-Cat 1 upgrade pathway is completely irrelevant, misleading, and unprofessional for a masters returner with a finish goal. It implies racing license progression, which has nothing to do with this event or persona.

### 8. [critical] ×1  (road/masters_returner)
> Weekly Volume check FAILED in the preview gate and the issue is unresolved in the plan text. The guide cannot be sent when a fundamental volume metric is flagged as incorrect — this could mean prescribed weekly hours contradict the athlete's 8 h/week target, which would undermine the entire training structure.

### 9. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the athlete's discipline is MTB, but the guide contains explicit 'Road Skills', 'Road Race Strategy', and 'Category 5 to Category 1 Pathway' sections. MTB athletes train for trail/technical skills, not road racing categories. This content is wrong for the athlete and will confuse or mislead them.

### 10. [critical] ×1  (mtb/ambitious_first_timer)
> Gran Fondo Guadeloupe is a road/gravel mass-participation event, not an MTB race. The plan persona and discipline field say 'mtb', which is almost certainly an intake error or system misclassification — but the guide was generated and accepted with that tag, meaning either the race-discipline pairing was never validated or the wrong template was applied. Sending an MTB-labelled plan for a road gran fondo (or vice versa) is a fundamental coaching error.

### 11. [major] ×1  (gravel/time_crunched_parent)
> Fueling rate of 54 g carbs/hour is below current evidence-based recommendations for a ~5.75-hour effort. Contemporary sports nutrition guidance (and most coaching businesses) prescribes 80–90+ g/h for efforts exceeding ~2.5 hours when the athlete is trained to absorb it. 54 g/h may leave this athlete under-fueled over nearly 6 hours of racing in a hot Caribbean climate.

### 12. [major] ×1  (gravel/time_crunched_parent)
> The guide includes a 'Women-Specific Considerations' section heading in the table of contents, but the truncated text never delivers it. If the section is present in the full document it needs to be verified for accuracy; if it is missing, the broken ToC entry is embarrassing.

### 13. [minor] ×2  (gravel/ambitious_first_timer, gravel/time_crunched_parent)
> Long ride duration range cited as '3.1–5.2 hours' in the Weekly Structure section — the lower bound of 3.1 h seems very precise and slightly odd for Week 1 of a base phase for an 8 h/week athlete; worth verifying this matches the actual calendar anchors.

### 14. [major] ×1  (road/weekend_warrior)
> The preview flagged 'Taper Intensity: WARN' but the guide text contains no acknowledgement or mitigation of this concern. If taper intensity is miscalibrated (e.g., short sharp efforts are set too hard or not hard enough relative to the athlete's RPE anchor), the athlete arrives at the race either flat or fatigued. At minimum the guide should note that taper sessions are short and controlled, not a continuation of peak-week intensity.

### 15. [major] ×1  (road/weekend_warrior)
> The preview flagged 'TSS Progression: WARN' with no in-guide explanation. For an athlete without a known FTP, TSS is already approximate, but a progression warning suggests a week-to-week ramp issue (likely >10% in a non-recovery week or an inverted step). This should either be corrected in the calendar or briefly addressed in the Phase Progression section so the coach can stand behind the load structure.

### 16. [major] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section in the TOC — if this covers road-specific cornering, criterium positioning, or peloton dynamics rather than gravel-specific technical skills (loose surface descending, mud, creek crossings, etc.), it is wrong-discipline content for a gravel athlete.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> Race day listed as 'Monday, November 30, 2026' — November 30, 2026 is actually a Monday, so this is technically correct, but L'Étape events are virtually always held on weekends (Sundays). The guide should flag this unusual weekday race date explicitly so the athlete double-checks, not just verify the year/date match. The current wording may give false confidence.

### 18. [major] ×1  (road/time_crunched_parent)
> Off-days listing contradiction — the guide states 'Off days: Monday, Friday, Thursday' which is THREE off days listed in a jumbled order (Thursday appears after Friday), yet the athlete has a 4-day training week with 5 hours/week. Three off days plus 4 training days equals 7 days, which is fine arithmetically, but listing 'Friday, Thursday' out of calendar order reads as a generation error and will erode trust.

### 19. [major] ×1  (road/time_crunched_parent)
> FTP test note says 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan. With only one FTP test implied (FTP Tests check = PASS, FTP Test Frequency = WARN), telling the athlete the result governs '6 weeks' is internally inconsistent with the plan length and will cause confusion about when zones should be updated.

### 20. [major] ×1  (road/time_crunched_parent)
> Long ride duration framing is mismatched to the race. The guide describes peak long rides of '1.5–2.5 hours' and then immediately warns this is shorter than ideal for the race distance — yet then suggests a '3–4 hour' ride target. For a ~4.5-hour event the plan's own prescribed ceiling (2.5 hrs) is acknowledged as inadequate, but no concrete resolution is given within the plan structure. This creates an unresolved contradiction the athlete cannot act on without coach intervention.

### 21. [major] ×1  (road/masters_returner)
> TSS Progression check is WARN (not PASS). A TSS ramp that is either too aggressive or inconsistent for a 55-year-old masters returner is a meaningful coaching error and a potential injury/overtraining risk. The guide text does not acknowledge or mitigate this issue.

### 22. [major] ×1  (road/masters_returner)
> Zone 1 (Active Recovery) in the zone chart lists no % FTP range (only 0–99 W is shown, with the % FTP column left blank). Every other zone has a % FTP figure. This is an inconsistency that looks like a rendering/template bug and erodes trust in the zone table.

### 23. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' section appears in the table of contents. L'Étape Ciudad de México is a gran fondo (mass-participation sportive), not a road race with tactical racing strategy. Providing road-race tactical content (attacking, positioning in a peloton for competition) is wrong-discipline content for a finish-goal fondo rider and could confuse the athlete.

### 24. [major] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the full guide. This is deeply inappropriate for a 'veteran podium chaser' with 16 years of riding experience. It reads as generic boilerplate inserted for a beginner/Cat 5 racer, which will undermine the athlete's confidence in the plan's personalization and is factually irrelevant to their situation.

### 25. [major] ×1  (road/veteran_podium_chaser)
> The athlete is described as 'Intermediate level' in the methodology justification ('16 years of cycling experience at Intermediate level'). A rider with 16 years of experience and a 310W FTP chasing a podium is not Intermediate — this label contradicts the persona ('veteran podium chaser') and will erode trust in the plan's personalization.
