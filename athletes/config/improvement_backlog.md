# Improvement backlog — 2026-09-02

**Quality 1.97** · avg coach 6.12/10 · contract pass 100% · load 12.88/plan · 12 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [major] ×4  (gravel/masters_returner, gravel/time_crunched_parent, mtb/weekend_warrior, road/weekend_warrior)
> Long ride duration range cited as '2.1–3.5 hours' in the Weekly Structure section. For a 68-mile MTB gran fondo with an estimated race duration of ~4.6 hours, the peak long ride should reach at least 3.5–4 h; the upper bound as written is too low and may leave the athlete underprepared for race-day duration demands.

### 2. [critical] ×1  (gravel/time_crunched_parent)
> Road Race Strategy and Category 5-to-1 Pathway sections are included in a GRAVEL gran fondo plan. These are road-racing constructs (USA Cycling Cat system, criterium/road-race tactics) that are irrelevant and confusing for a gravel gran fondo athlete — this is a discipline mismatch that will undermine athlete trust.

### 3. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section (visible in the table of contents) appears to be populated with road-racing content rather than gravel-specific skills (e.g., loose-surface cornering, tire pressure management, gravel descending). Sending road-specific skills coaching to a gravel racer is embarrassing and incorrect.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> The table of contents and guide body include sections titled 'Road Skills', 'Road Race Strategy', and 'Category 5 to Category 1 Pathway'. This athlete is a GRAVEL racer. Road race tactics and a Cat 5-to-1 upgrade pathway are completely wrong-discipline content and are embarrassing to send to a gravel customer.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the Table of Contents explicitly lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway.' This is an MTB gran fondo, not a road criterium or road stage race. Cat 5–1 pathway content is entirely irrelevant and embarrassing for an MTB athlete.

### 6. [critical] ×1  (mtb/weekend_warrior)
> Fueling carb figure is suspiciously inconsistent: the JSON specifies 61 g/hr, but the guide's own duration estimate (~4.6 h) would yield roughly 281 g total. The guide must state the per-hour figure clearly and consistently; if the body text contradicts or omits the 61 g/hr number, the athlete gets no actionable fueling guidance for their specific race.

### 7. [critical] ×1  (road/weekend_warrior)
> Off-day schedule lists Saturday, Friday, AND Sunday as off days — that is three consecutive days off in a 6 h/week plan, which is incoherent and contradicts the 4 training days per week stated later in the same document. At minimum one of these days must be a training day; the auto-check flags need to be reconciled with the actual calendar text.

### 8. [critical] ×1  (road/weekend_warrior)
> Long-ride day is listed as Tuesday. For a road-based weekend warrior, placing the longest ride of the week on a Tuesday mid-week is atypical and conflicts with the persona description ('weekend warrior'). If Saturday and Sunday are both off days this is especially problematic — the athlete's life structure makes a weekend long ride far more realistic, and this will likely cause immediate non-compliance.

### 9. [critical] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' appears in the table of contents and presumably in the body. This is USA Cycling criterium/road race licence upgrade content — completely irrelevant and inappropriate for a gran fondo athlete. A paying gran fondo customer seeing a Cat 5 upgrade pathway will immediately question whether this is their plan at all. Must be removed.

### 10. [critical] ×1  (road/time_crunched_parent)
> The countdown reads '96 days from today' but the plan start date is 2026-09-07 and the race is 2026-12-07 — that is exactly 91 days. '96 days' is wrong and will erode trust in the entire document the moment the athlete checks a calendar.

### 11. [critical] ×1  (gravel/time_crunched_parent)
> Table of contents and plan body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This athlete is doing a gravel gran fondo with a goal of 'finish' — road race strategy and a Cat 5→Cat 1 upgrade pathway are completely wrong-discipline, wrong-goal content that will confuse and embarrass.

### 12. [critical] ×1  (gravel/masters_returner)
> Contents list and body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — these are road-racing constructs (USA Cycling category upgrade system) that have no relevance to a gravel event and will confuse or embarrass the athlete.

### 13. [critical] ×1  (gravel/masters_returner)
> Elevation listed as '650 ft' for GFNY Cozumel 96 mi. Cozumel is a flat island; while low elevation is plausible, this figure is suspiciously round and was not in the verified race data provided. It should either be confirmed from the race database or omitted rather than stated as fact — a wrong elevation figure undermines trust in the whole plan.

### 14. [major] ×1  (gravel/time_crunched_parent)
> Athlete weight is listed as 175 lbs / 79.4 kg in the guide, but this figure does not appear in the plan JSON — it is either fabricated by the generator or pulled from an unverified source. The JSON has no weight field, so this number should not be stated as fact; it risks contradicting the athlete's actual body weight.

### 15. [major] ×1  (gravel/time_crunched_parent)
> The fueling section references a calculated race duration of ~3.31 hours and 65 g carbs/hour, but the truncated guide text does not show these numbers surfaced clearly to the athlete in the Nutrition Strategy section. If the nutrition section was cut off before the per-hour target and duration-based total were presented, the athlete receives no actionable fueling numbers — a significant gap for a podium-goal racer.

### 16. [major] ×1  (gravel/time_crunched_parent)
> The TSS Progression check flagged WARN in the preview. The guide text contains no acknowledgement or coaching note explaining the irregular TSS ramp to the athlete (e.g., a planned loading week or recovery dip). A WARN-level flag should either be resolved in the calendar or footnoted in the guide so the coach can defend it.

### 17. [major] ×1  (mtb/weekend_warrior)
> Off days listed as 'Friday, Thursday, Monday' — three off days totalling four training days in a 7-day week. For a 6 h/week athlete on Time-Crunched methodology, three full off days is on the high side but not impossible; however, listing them in non-chronological order (Friday before Thursday) reads as a template error and will confuse the athlete.

### 18. [major] ×1  (mtb/weekend_warrior)
> FTP Test Frequency check flagged WARN in the preview checks but no explanation or mitigation appears in the guide text. The guide states 'the test result sets ALL your training zones for the next 6 weeks' — over a 9-week plan this language implies a second test may be needed but none is addressed, leaving the athlete uncertain.

### 19. [major] ×1  (road/weekend_warrior)
> The guide contains a 'Category 5 to Category 1 Pathway' section (visible in the table of contents). This athlete's goal is simply to finish GFNY Miami — there is zero relevance to a Cat upgrade pathway, which applies to licensed USA Cycling road racing, not gran fondo participation. This content is wrong for this athlete and will confuse or mislead them.

### 20. [major] ×1  (road/weekend_warrior)
> Taper Intensity flagged WARN by the automated preview checks, but the guide text does not address or resolve this warning. If intensity during taper is miscalibrated, the athlete arrives at race day either flat (too easy) or fatigued (too hard) — this must be reviewed and the taper section corrected or explicitly annotated before sending.

### 21. [major] ×1  (road/weekend_warrior)
> FTP Test Frequency is flagged WARN. For a 9-week plan, the guide states 'The test result sets ALL your training zones for the next 6 weeks' — implying a single retest is expected, but the warn flag suggests the retest cadence in the actual calendar may be off. This inconsistency between the guide text and the calendar gate must be reconciled explicitly.

### 22. [major] ×1  (road/time_crunched_parent)
> Off-day list is presented as 'Saturday, Thursday, Monday' — an unusual ordering that also leads with Saturday, the conventional long-ride day for time-crunched athletes. The plan then states long rides are on Sunday, which is fine, but listing Saturday first among off days will confuse readers. The ordering should be logical (e.g., Monday, Thursday, Saturday) and must not imply Saturday is an off day if it is used elsewhere in the calendar.

### 23. [major] ×1  (gravel/time_crunched_parent)
> The 'Road Skills' section (visible in the ToC) is not shown in the truncated text, but if it contains road-racing cornering or criterium-specific skills rather than gravel-specific skills (loose surface cornering, technical descending, gravel bike handling), it would be mismatched to the discipline. Needs verification before send.

### 24. [major] ×1  (gravel/time_crunched_parent)
> Preview check flags 'FTP Test Frequency: WARN' but the guide text never surfaces this to the athlete — no explanation of how many tests are scheduled or why the frequency is flagged. A paying athlete deserves to know if something is borderline so they can plan around it.

### 25. [major] ×1  (gravel/masters_returner)
> Equipment checklist specifies a 'road bike' as the mandatory training bike for a gravel discipline athlete. This should read 'gravel bike (or road bike if that is what you train on)' — sending a gravel racer a plan that says 'road bike, in good working order' signals the plan was not built for them.
