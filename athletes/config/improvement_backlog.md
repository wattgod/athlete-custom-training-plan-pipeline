# Improvement backlog — 2026-09-26

**Quality 3.0** · avg coach 6.75/10 · contract pass 75% · load 10.62/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> Wrong discipline content included: 'Road Skills' and 'Road Race Strategy' chapters appear in the table of contents for a GRAVEL athlete. These sections should be Gravel Skills and Gravel/Gran Fondo Race Strategy. Sending road-race tactics to a gravel rider is a clear discipline mismatch that will undermine credibility.

### 2. [critical] ×1  (gravel/masters_returner)
> Countdown '56 days from today' is hardcoded and internally inconsistent: the plan start date is 2026-09-28 and race date is 2026-11-21, which is 54 days — not 56. More importantly, 'today' is undefined and will be wrong the moment the email is opened on any day other than the generation date. Either compute the correct value or omit the countdown entirely.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Equipment checklist mandates a 'road bike' — this is an MTB event (discipline: mtb). The mandatory kit item should reference an MTB/gravel bike appropriate for the event, not a road bike. Sending this to an MTB athlete is embarrassing and could lead to a genuinely wrong equipment choice.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Section headings include 'Road Skills' and 'Road Race Strategy' — visible in the table of contents and confirmed in the truncated text. Gran Fondo Guadeloupe on MTB requires trail/technical riding cues, not road-racing tactics. This is wrong-discipline content that undermines credibility immediately.

### 5. [critical] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full document. This athlete's goal is simply to FINISH a 99-mile gran fondo — she is not racing in a USA Cycling license category system. This section is irrelevant, misleading, and makes the plan look like a copy-paste error from a different template. It must be removed entirely.

### 6. [major] ×1  (gravel/masters_returner)
> Zone Distribution check FAILED (per preview_checks). The guide text claims '~70% of riding stays genuinely easy,' but the automated gate flagged this as a FAIL — meaning the actual weekly calendar does not match that stated distribution. The prose and the calendar contradict each other; this must be reconciled before delivery.

### 7. [major] ×1  (gravel/masters_returner)
> TSS Progression is flagged WARN and Taper Intensity is flagged WARN. Neither issue is addressed or explained anywhere in the visible guide text. For a masters returner (age 55, post-layoff), a poorly structured taper or erratic TSS ramp is a real injury/overtraining risk that the coach's notes should at minimum acknowledge.

### 8. [major] ×1  (gravel/masters_returner)
> Long ride duration stated as '1.9–3.2 hours' in the Weekly Structure section. Given a 6 h/week budget and a 99-mile/~6.7-hour target event, a peak long ride of only 3.2 hours is borderline low but potentially acceptable under Time-Crunched methodology — however the range is never explained or justified for a 6.7-hour race. The athlete may reasonably panic seeing this number without a clear rationale.

### 9. [major] ×1  (mtb/ambitious_first_timer)
> The plan is 11 weeks but the race is 10 weeks away (plan_start_date 2026-09-28, race 2026-12-07). The JSON note explains this is intentional (athlete starts one week late), but the plan guide never communicates this to the athlete — they will open the plan, count 11 weeks, compare to their calendar, and be confused about which week to start on. A single sentence explaining the delayed start is needed.

### 10. [major] ×1  (mtb/ambitious_first_timer)
> FTP Test Frequency flagged WARN in preview checks. The guide tells the athlete to do a Week 1 field test but never specifies a re-test cadence or when (if ever) the anchor gets updated across an 11-week plan. For a first-timer who will improve substantially, this leaves mid-plan zone guidance unanchored.

### 11. [major] ×1  (road/time_crunched_parent)
> The guide includes a 'Category 5 to Category 1 Pathway' section. This athlete's goal is simply to FINISH a 99-mile gran fondo — Cat 5 to Cat 1 racing pathway content is irrelevant, potentially confusing, and makes the plan look like it was assembled from a generic template. It does not belong in a finish-goal, time-crunched, gran fondo plan.

### 12. [major] ×1  (road/time_crunched_parent)
> The guide text is truncated mid-sentence ('General guid...') in the Nutrition section. While this may be a rendering artifact in the QA preview, if the athlete receives an incomplete document it is unprofessional and potentially harmful (missing pre-workout fueling instructions).

### 13. [major] ×1  (road/weekend_warrior)
> Zone Distribution automated check is FAIL and the guide text does not address or justify this. A paying customer will receive a plan with a known distribution problem that neither the document nor a coach note explains. Either the distribution needs to be corrected in the calendar workouts, or the guide must transparently explain why the prescribed distribution deviates from the stated ~70% easy / 30% intensity split.

### 14. [major] ×1  (road/weekend_warrior)
> Fueling recommendation of 55 g carbs/hr for a projected ~5.75-hour effort is under-dosed by current sport-nutrition consensus (which supports 80–120 g/hr for multi-transporter carb blends at that duration). For a finish-goal athlete who will be on-course for nearly 6 hours, this risks bonking in the final third of the race — exactly what the plan is designed to prevent. Either the number should be raised or a clear rationale given for the conservative figure.

### 15. [major] ×1  (road/weekend_warrior)
> Taper Intensity is flagged WARN by the automated gate and is not addressed anywhere in the visible guide text. The taper section says 'short, sharp efforts keep the engine awake' but gives no corrective context about what the intensity concern actually is. This should either be resolved in the calendar or annotated in the Race Week section.

### 16. [minor] ×2  (road/masters_returner, road/weekend_warrior)
> Long-ride duration range stated in the guide ('1.5–2.2 hours') is notably short for a 78-mile / ~5.75-hour race, even for a Time-Crunched athlete. The 'Biggest Opportunity' callout partially mitigates this but then suggests only '3–4 hour' occasional long rides — that ceiling should arguably be higher (4–5 h) for adequate race-day durability simulation at this event distance.

### 17. [major] ×1  (road/masters_returner)
> Zone-distribution WARN is unresolved and unexplained to the athlete. The guide states '~70% easy' but the automated check flagged WARN on Zone Distribution, meaning the calendar workouts may not actually deliver that split. If the real schedule skews too hard (common in short Time-Crunched plans), the stated methodology promise is broken. A coach sign-off should confirm the actual distribution or add a caveat.

### 18. [major] ×1  (road/masters_returner)
> TSS Progression is flagged WARN, yet the guide contains no acknowledgment or mitigation. For a 55-year-old masters returner, an irregular TSS ramp is a real injury/overtraining risk, not just a metrics warning. The guide should either note that week-to-week load is deliberately non-linear (and why) or the calendar should be corrected before sending.

### 19. [major] ×1  (gravel/time_crunched_parent)
> Table of contents and apparent section heading include 'Road Race Strategy' — this athlete is racing a gravel gran fondo, not a road race. Gravel gran fondos have distinct tactical considerations (loose surface descending, self-sufficient fueling, variable terrain pacing). Sending a road race strategy section to a gravel athlete is a discipline mismatch that will undermine trust in the entire plan.

### 20. [major] ×1  (road/veteran_podium_chaser)
> Three automated preview checks flagged WARN (Weekly Volume, TSS Progression, Taper Intensity) but the guide text gives no indication these were resolved or deliberately accepted. Weekly Volume and TSS Progression warnings together suggest the actual calendar may under-deliver the 13h target or have a non-standard load ramp — this cannot be cleared from the truncated text alone and must be verified before sending.

### 21. [major] ×1  (road/veteran_podium_chaser)
> Taper Intensity flagged WARN: for a podium-chasing veteran, a poorly calibrated taper (either too blunt or too soft) is race-defining. The guide text describes the taper philosophy correctly in prose but the automated check suggests the calendar execution may not match — this is the highest-stakes week of the plan and the discrepancy must be confirmed resolved.

### 22. [major] ×1  (road/time_crunched_parent)
> 'Road Race Strategy' section (also in the ToC) references competitive road-race tactics. This is a mass-participation gran fondo with a finish goal, not a road race. Strategy content should be replaced with gran-fondo-appropriate guidance (pacing by power, aid-station planning, managing the field surge at the start).

### 23. [major] ×1  (road/time_crunched_parent)
> The fueling section prescribes 55 g carbs/hour but never tells the athlete her estimated finish time (~6.7 h per the plan data). Without anchoring the hourly rate to a projected duration and total carb target, a finish-goal athlete cannot build a practical race-day fueling plan. The estimated finish time and total carb/fluid quantities should be stated explicitly.

### 24. [minor] ×1  (gravel/masters_returner)
> The guide references 'Strength training: Included (bodyweight)' in the at-a-glance box and a Strength section in the TOC, but the truncated text never confirms these are gravel/endurance-appropriate movements (e.g., hip hinge, single-leg work). Given the discipline, explicit callout that gym sessions do not include heavy lower-body loading close to key ride days is warranted for a 55-year-old masters athlete.

### 25. [minor] ×1  (gravel/masters_returner)
> Off days listed as 'Saturday, Thursday' in the at-a-glance section, while the long ride is placed on Sunday. For a gravel athlete whose target event is on a Saturday (2026-11-21 is a Saturday), having Saturday as a permanent off day and never practicing Saturday-morning race-simulation efforts is a minor but real race-prep gap worth flagging to the athlete.
