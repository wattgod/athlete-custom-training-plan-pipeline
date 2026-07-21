# Improvement backlog — 2026-07-21

**Quality 2.42** · avg coach 5.62/10 · contract pass 100% · load 10.5/plan · 8 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/masters_returner)
> Gravel Skills section is explicitly listed in the table of contents and presumably in the full plan body. This is a verified ROAD event (Sea Otter Ciclobrava, Girona). Gravel skills content has zero relevance here and will embarrass the business if a road racer reads advice about loose-surface cornering and tyre choice.

### 2. [critical] ×1  (road/masters_returner)
> The race is listed as 'Sea Otter Ciclobrava' but the Sea Otter Classic is a Monterey, CA event; the Ciclobrava is a separate Girona/Costa Brava event. The plan conflates the two names into a single hybrid race name ('Sea Otter Ciclobrava'), which will confuse the athlete and erodes trust in the verified-database claim.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the plan is flagged as MTB, yet the table of contents and body include 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section. GFNY Pittsburgh is a road gran fondo, not an MTB race. The discipline field says 'mtb,' which is itself likely wrong for this event, but regardless, road-racing category upgrade pathways and road race strategy content do not belong in an MTB plan. One of these is wrong; either the discipline tag or the content must be corrected before sending.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Missing MTB-specific skills content — if the discipline is truly MTB, the plan has no trail skills section (cornering, braking, technical descending, body position), which is a glaring omission for an ambitious first-timer on a mountain bike. If the discipline is road/gravel (matching the actual GFNY Pittsburgh event), the plan should not be labeled MTB at all.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Wrong discipline content: the table of contents and guide body explicitly include 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections. This athlete is an MTB rider targeting a gran fondo — road racing categories and road race tactics are irrelevant and actively misleading. These sections must be replaced with MTB/gran-fondo-appropriate content (e.g., climbing tactics, technical descending for mixed terrain, gran fondo pacing strategy).

### 6. [critical] ×1  (mtb/weekend_warrior)
> Long-ride ceiling of 1.5 hours is dangerously inadequate for a 68-mile event with an estimated 4.7-hour finish time. The guide even acknowledges this is short ('your long rides are shorter than ideal') but then caps peak long rides at 1.5 h — a Time-Crunched plan for a 5 h/week athlete can and should target at least 2.5–3 h long rides by the Peak phase. Sending this as written will leave the athlete undertrained for race-day duration demands.

### 7. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the persona JSON flags discipline='mtb' but the entire plan — race name, race database entry, location, and even the dedicated 'Gravel Skills' section — is built around a gravel event (Grassroots Gravel). The plan cannot be both an MTB plan and a gravel plan. Either the discipline tag is wrong and should be 'gravel', or the wrong race was matched. This must be resolved before sending — an MTB athlete preparing for a gravel race needs gravel-specific skills content, not MTB-specific skills content, and vice versa.

### 8. [critical] ×1  (mtb/weekend_warrior)
> Zone 1 and Zone 2 are missing their '% FTP' column values in the zone chart (the cells are blank where 56-75% appears only for Zone 2 and nothing appears for Zone 1). Zone 1 shows only a raw watt range (0-97W) with no percentage anchor. This is the zone the athlete will ride most and the omission undermines the entire zone reference.

### 9. [major] ×1  (road/masters_returner)
> TSS Progression check returned WARN in the preview but no explanation or mitigation is surfaced anywhere in the guide text. For a masters returner this is a meaningful risk flag that a real coach would address explicitly.

### 10. [major] ×1  (road/masters_returner)
> Off days listed in the at-a-glance summary are Saturday, Tuesday, and Wednesday — that is three consecutive or near-consecutive off days mid-week, leaving only four training days (Mon, Thu, Fri, Sun). For a Time-Crunched athlete targeting 6 h/week with a 1.9–3.2 h long ride, this clustering of rest days is unusual and potentially wastes the week's training density; it needs a clear rationale or correction.

### 11. [major] ×1  (road/masters_returner)
> Fueling strategy from the plan JSON specifies 57 g carbs/hour for an 8.3-hour race effort, yet the Recovery Protocol section prescribes only 71–85 g carbs in the post-ride window — plausible for a short ride but potentially under-fuelling for an 87-mile event. The in-ride fueling target (57 g/h × 8.3 h ≈ 473 g total) is never surfaced in the visible guide text, leaving the athlete without race-day fueling guidance.

### 12. [major] ×1  (mtb/ambitious_first_timer)
> Experience-level contradiction — the athlete has '1 Years Riding' yet the plan text explicitly calls them 'Intermediate level.' One year of riding is a beginner by almost any coaching standard. Labeling them Intermediate could lead to inappropriate training load expectations and undermines coach credibility.

### 13. [major] ×1  (mtb/ambitious_first_timer)
> TSS Progression flagged WARN in preview checks but no mitigation or note is visible in the guide text. A WARN on TSS progression means week-over-week load jumps may exceed the 10% rule; this is a real injury-risk issue for a first-timer and should either be corrected in the calendar or explicitly acknowledged with guidance.

### 14. [major] ×1  (mtb/ambitious_first_timer)
> Long ride duration range stated as '3.3–5.5 hours' in the Weekly Structure section. For a 9h/week athlete targeting a ~5h race, a 5.5-hour long ride is on the outer edge and acceptable in Peak, but 3.3h as a starting point in Week 1 for someone with only 1 year of riding experience and a finish-only goal warrants a coach note — and more importantly the range should be verified against the actual calendar to ensure it isn't padded or invented.

### 15. [major] ×1  (gravel/masters_returner)
> The custom zone label 'GS G Spot' is inappropriate for a professional coaching document delivered to a paying female athlete. Regardless of its technical meaning (88-93% FTP sweet-spot zone), the name reads as sexually suggestive and will likely embarrass or offend the customer. It should be renamed (e.g. 'Sweet Spot' or 'Zone 3+') before sending.

### 16. [major] ×1  (gravel/masters_returner)
> The preview check flagged FTP Test Frequency as WARN, but the guide text does not acknowledge or explain this. The FTP testing protocol section simply describes how to execute a 20-minute test and says 'the test result sets ALL your training zones for the next 6 weeks' — yet in a 10-week plan for an athlete without a known FTP baseline, the frequency/timing of tests should be explicitly addressed so the athlete is not left confused about when and how often to retest.

### 17. [major] ×1  (gravel/veteran_podium_chaser)
> Countdown displayed as '72 days from today' conflicts with the plan data: plan_start_date is 2026-08-03 and race_date is 2026-10-01, which is 59 days — not 72. The guide appears to have calculated the countdown from a different reference point (possibly plan generation date rather than plan start date). If the athlete reads '72 days' and cross-checks a calendar they will immediately distrust the document.

### 18. [minor] ×2  (gravel/veteran_podium_chaser, road/masters_returner)
> The long-ride duration range cited in the Weekly Structure section ('3.1–5.2 hours') is suspiciously precise and unexplained. For a 65-mile gravel race with an expected finish around 4–4.5 hours, a ceiling of 5.2 hours is defensible, but the lower bound of 3.1 hours reads as an auto-generated artifact rather than a coach's round number, which undermines credibility.

### 19. [major] ×1  (road/masters_returner)
> A 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full document. This is a licensed road-racing category progression framework — it is entirely irrelevant and potentially confusing for a 60-year-old masters athlete whose sole goal is to finish a granfondo. It implies competitive category racing, which contradicts the athlete's goal and persona, and could undermine trust in the whole document.

### 20. [major] ×1  (road/masters_returner)
> The automated preview flagged 'Weekly Volume: WARN' but the guide text contains no acknowledgement, caveat, or explanation of why volume may be unusual. A paying masters athlete whose volume is outside normal bounds deserves a note — either reassurance that the flag was reviewed and intentional, or a clear heads-up. Silently shipping a warned metric is a quality-control failure.

### 21. [major] ×1  (mtb/weekend_warrior)
> Discipline mismatch throughout the skills and strategy sections: 'Road Skills' content (group riding dynamics framed as road peloton behavior, etc.) does not apply to a mass-start gran fondo on mixed/MTB terrain. Even if the Felice Gimondi gran fondo is a road-style event, the plan was generated for discipline='mtb' and the content reflects neither MTB skills nor gran fondo-specific road strategy coherently.

### 22. [major] ×1  (mtb/weekend_warrior)
> The '4x4min at 110% FTP' example in Workout Execution prescribes Zone 5 / VO2max intervals for a 54-year-old masters weekend warrior whose goal is simply to finish. While VO2max work can be included, the example normalizes very high intensity without any masters-specific caveat — this contradicts the plan's own Masters Considerations section (which we cannot read in full but is listed in the ToC) and may alarm or injure this athlete.

### 23. [major] ×1  (mtb/weekend_warrior)
> The guide prominently includes a 'Gravel Skills' section in the table of contents. If the athlete is truly an MTB rider, gravel cornering/handling skills content is wrong-discipline material. If the athlete is a gravel rider, the 'mtb' discipline tag in the system is the error. Either way, the skills section must match the confirmed discipline before the plan goes out.

### 24. [major] ×1  (mtb/weekend_warrior)
> FTP Test Frequency check returned WARN in the preview checks but is not acknowledged or explained anywhere in the guide. A 10-week plan with a WARN on test frequency should either clarify the testing schedule to the athlete or note why fewer tests are appropriate — leaving it silent is a coaching gap.

### 25. [minor] ×1  (road/masters_returner)
> The countdown says '61 days from today' — this is a dynamic field that will be stale the moment the email is queued or delayed; it should either be removed or locked to the send date to avoid confusion.
