# Improvement backlog — 2026-08-10

**Quality -0.1** · avg coach 5.25/10 · contract pass 100% · load 15.88/plan · 14 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [major] ×4  (gravel/ambitious_first_timer, gravel/masters_returner, mtb/ambitious_first_timer)
> Long ride duration range is cited as '2.7-4.5 hours' in the Weekly Structure section. For a goal race estimated at 4.7+ hours, the upper bound of the long ride (4.5 h) is only marginally below race duration, which is acceptable — but combined with the likely underestimated race duration in the fueling section, the athlete may never actually train at true race duration. Worth verifying the peak long ride hits at least 80% of realistic race time.

### 2. [critical] ×1  (road/weekend_warrior)
> Zone table is missing power ranges for Zones 1 and 2. Zone 1 shows '0-96W' but Zone 2 only shows '97-132W' with no lower FTP% anchor displayed; more importantly, neither zone shows a clear % FTP column value in the rendered text — the columns for Zone 1 % FTP and % LTHR are completely blank. For a plan whose entire execution depends on athletes hitting prescribed power targets, missing zone-1 percentage anchors is a meaningful error that will confuse athletes without a power meter.

### 3. [critical] ×1  (road/weekend_warrior)
> The guide contains a 'Category 5 to Category 1 Pathway' section listed in the Table of Contents. This is a USA Cycling amateur road racing licensing concept that is entirely irrelevant — and potentially confusing — for a weekend warrior whose sole goal is to 'finish' a gran fondo. It implies a competitive racing ladder this athlete has no interest in and contradicts the persona and goal.

### 4. [critical] ×1  (gravel/masters_returner)
> Table of contents and plan body include a 'Category 5 to Category 1 Pathway' section — this is a road-racing licensing/category concept that is completely irrelevant and misleading for a gravel athlete whose only goal is to finish a single A-race. It should not exist in this plan.

### 5. [critical] ×1  (gravel/masters_returner)
> Table of contents and plan body include a 'Road Race Strategy' section — this athlete is racing gravel, not a road race. Gravel and road racing have fundamentally different strategies (terrain, nutrition stops, self-sufficiency, tire/gear choices). Sending road-race strategy content to a gravel racer is a discipline mismatch that undermines coaching credibility.

### 6. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections are listed in the Table of Contents and apparently included in the guide. This athlete is a gravel gran fondo finisher, not a licensed road racer. Cat 5–1 upgrade pathways are entirely irrelevant and will confuse or mislead the athlete; they also expose the plan as templated rather than custom.

### 7. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section title in the ToC is ambiguous but the presence of 'Road Race Strategy' alongside it strongly suggests road-specific cornering/peloton content was included verbatim — wrong discipline content for a gravel event.

### 8. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the plan JSON says discipline='mtb' but the race is 'Gravel Roll - Pecan Shaker,' a verified gravel event. The guide is titled as a gravel plan and includes a 'Gravel Skills' section — yet the persona and internal tagging are MTB. Either the wrong template fired or the discipline field is wrong. Either way, the athlete is receiving a plan whose framing, skills content, and identity are internally inconsistent and do not match the actual event.

### 9. [critical] ×1  (mtb/ambitious_first_timer)
> The 'Gravel Skills' section heading appears in the table of contents but the guide excerpt shows MTB-persona JSON driving it. If 'Gravel Skills' drills are in the body (likely, given the section exists), they are appropriate for the race but contradict the MTB discipline tag — and vice versa if MTB-specific skills (rock gardens, drops, technical descending) were injected. The section must be audited; content for the wrong sub-discipline would be embarrassing and potentially unsafe advice.

### 10. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete's plan JSON declares discipline = 'mtb', yet the guide is written and branded as a gravel plan throughout — title reads 'Alentejo Gravel 80mi', and a 'Gravel Skills' chapter is explicitly listed in the table of contents. MTB and gravel are distinct disciplines with different technical demands (singletrack handling, body position, braking technique, tire/suspension setup). Sending a gravel-skills chapter to an MTB racer is both wrong and embarrassing.

### 11. [critical] ×1  (mtb/ambitious_first_timer)
> Race name vs. discipline contradiction is unresolved for the athlete: the verified race is called 'Alentejo Gravel' but the plan discipline is 'mtb'. The guide makes no attempt to clarify this for the athlete — it simply inherits both data points silently. If the race truly is a gravel event, the discipline field is wrong and the whole plan methodology/skills content may be miscategorised; if it is MTB, the race name branding throughout the guide is wrong. Either way this must be resolved before sending.

### 12. [critical] ×1  (mtb/ambitious_first_timer)
> FTP watts displayed as body weight in pounds: the profile card reads '122 lbs Weight' AND '122W FTP' — the athlete's FTP value (122 W) has been incorrectly mapped to the weight field. The athlete's actual weight is unknown and should not be fabricated; this will seriously undermine trust.

### 13. [critical] ×1  (mtb/ambitious_first_timer)
> Wrong discipline content: the table of contents lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This is an MTB athlete targeting a point-to-point gran fondo/sportive (Cycling Shimanami). Road racing categories and criterium/road-race tactics are completely irrelevant and embarrassing.

### 14. [critical] ×1  (mtb/ambitious_first_timer)
> Cycling Shimanami is a paved island-hopping route (Nishiseto Expressway / Shimanami Kaido) — it is a road/gravel event, NOT an MTB event. The plan metadata says discipline='mtb' but the race is on tarmac. Either the athlete selected the wrong discipline or the system assigned the wrong one. Sending an MTB-specific plan (with implied MTB skills content referenced in the ToC under 'Road Skills') for a fully paved 44-mile route is a meaningful coaching error that must be resolved before delivery.

### 15. [critical] ×1  (road/time_crunched_parent)
> A 'Gravel Skills' section appears in the table of contents for a road discipline athlete. Sending gravel-specific skills content to a road racer is a discipline mismatch that directly undermines credibility and signals the plan was not properly customised.

### 16. [major] ×1  (road/weekend_warrior)
> The athlete profile box inside the plan displays the FTP as 176 W, which is correct, but ftp_known is listed as false in the plan JSON. If the athlete did not supply an FTP and it was estimated, the guide must clarify it is an estimate and instruct the athlete to verify it at their first FTP test — presenting an estimated figure as a confirmed fact risks 15 weeks of wrong-zone training.

### 17. [major] ×1  (road/weekend_warrior)
> Long ride duration is stated as '1.9-3.2 hours' in the Weekly Structure section. For a 6 h/week Time-Crunched athlete targeting a ~4.7 h race, a long ride ceiling of 3.2 h is reasonable, but 1.9 h as the floor in early base weeks seems low even for week 1 — this range should be verified against the actual calendar to confirm the stated numbers match what is scheduled, otherwise athletes may set incorrect expectations.

### 18. [major] ×1  (gravel/masters_returner)
> Zone chart is missing power values for Zone 1 (Active Recovery) and Zone 2 (Endurance) — the columns show '0-111W' for Z1 but no upper-bound watts are given for Z2 ('112-152W' appears but the %FTP column for Z1 is blank). Athletes rely on this table to set their head unit; incomplete rows will cause confusion.

### 19. [major] ×1  (gravel/masters_returner)
> The fueling section states an estimated race duration of 4.7 hours, but this figure is never reconciled anywhere in the visible guide text with the athlete's actual pace or experience level. For a 54-year-old masters returner on a hilly 68-mile gravel course (4,900 ft elevation), a more conservative estimate (5.5–6.5 h) may be appropriate. Underestimating race duration leads to dangerous under-fueling — 58 g carbs/hr for only 4.7 h could leave the athlete in a significant deficit if the race takes longer.

### 20. [major] ×1  (gravel/masters_returner)
> 'Road Skills' section appears in the table of contents — for a gravel event this should be gravel-specific skills (loose surface cornering, descending on gravel, tire pressure management, surface reading) not generic road skills. The content (not shown in truncated text) may be wrong for the discipline.

### 21. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression check returned WARN and was never resolved or explained to the athlete. A flagged progression issue means there may be a week-to-week TSS spike that risks overtraining or injury; this should either be fixed in the schedule or explicitly acknowledged in the guide text.

### 22. [major] ×1  (gravel/ambitious_first_timer)
> Fueling duration is listed as 4.7 hours for a 68-mile gravel race. For a 28-year-old first-timer on hilly Italian gravel (5,577 ft elevation), a realistic finishing time is closer to 5.5–7 hours. A 4.7 h fueling window will leave the athlete underprepared for the back half of the race — the hourly carb target (57 g/h) may also be on the low side if duration is underestimated.

### 23. [major] ×1  (mtb/ambitious_first_timer)
> The plan_weeks (8) is shorter than weeks_until_race (10), meaning the athlete starts 2 weeks late. This is noted as intentional in plan_note, but the guide contains zero explanation of this gap. A first-timer receiving an 8-week plan for a race 10 weeks away will be confused about what to do in weeks 1-2. The guide must explicitly tell the athlete when to start and what to do in the interim.

### 24. [major] ×1  (mtb/ambitious_first_timer)
> FTP Test Frequency check flagged WARN in the preview checks, yet the guide text says 'the test result sets ALL your training zones for the next 6 weeks' — in a 9-week plan that implies only one test, which may be insufficient. The guide provides no explicit schedule or rationale for when the retest occurs, leaving the athlete without actionable guidance on this flagged issue.

### 25. [major] ×1  (mtb/ambitious_first_timer)
> The 'Gravel Skills' section (listed in the table of contents) is inappropriate content for an MTB discipline plan regardless of the race name ambiguity. Even if the race turns out to be gravel, the athlete profile is tagged MTB; if the race is gravel the discipline tag should have been corrected upstream, not papered over with a gravel-skills chapter bolted onto an MTB plan.
