# Improvement backlog — 2026-07-25

**Quality -1.25** · avg coach 5.0/10 · contract pass 50% · load 15.62/plan · 10 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/weekend_warrior, mtb/ambitious_first_timer)
> Zone Distribution check FAILED in the preview checks, but the guide text contains no acknowledgment, correction note, or coaching caveat about zone balance. A failed automated check that is silently swallowed is a quality risk — either the plan text should reflect corrected distribution or the failure reason should be reviewed before sending.

### 2. [critical] ×2  (mtb/ambitious_first_timer, road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the plan body. This is a USA Cycling licensed racing category ladder — it is completely irrelevant and potentially confusing or off-putting for a gran fondo athlete whose stated goal is simply to finish. It belongs in a crit/road-race category racer's plan, not here. Sending this to a time-crunched 44-year-old gran fondo participant is embarrassing.

### 3. [critical] ×2  (mtb/ambitious_first_timer, road/time_crunched_parent)
> Zone Distribution check is flagged FAIL in the preview checks but there is no acknowledgement, correction, or coach note in the guide. If the prescribed zone distribution is misconfigured (likely too much Z3 gray-zone given the methodology), the plan's core methodology claim ('roughly 65% easy') may not actually be reflected in the calendar — meaning the athlete will train on a broken distribution.

### 4. [critical] ×1  (gravel/weekend_warrior)
> Chapter listed as 'Gravel Skills' but the race is 'Little Sugar MTB' — a mountain bike event in Bentonville, AR. The skills chapter should address MTB-specific skills (singletrack cornering, braking technique, rock gardens, technical climbing/descending) not generic gravel skills. Sending a gravel skills section to an MTB racer is a discipline mismatch that will immediately erode athlete trust.

### 5. [critical] ×1  (gravel/masters_returner)
> Table of contents includes 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' — this athlete is a gravel rider targeting a gran fondo finish, not a road racer seeking a licence upgrade. These sections are flatly wrong for the discipline and persona and would embarrass the business.

### 6. [critical] ×1  (gravel/masters_returner)
> Zone Distribution check flagged WARN in the preview but the guide never addresses or explains it. A polarized/Time-Crunched plan must validate that Z2+Z4-5 dominate and Z3 is minimised; leaving this unresolved means we cannot confirm the workload distribution is correct for the methodology.

### 7. [critical] ×1  (mtb/ambitious_first_timer)
> Wrong-discipline content: the guide explicitly includes 'Road Skills,' 'Road Race Strategy,' and a 'Category 5 to Category 1 Pathway' section. This is an MTB athlete targeting a gran-fondo-style MTB event (L'Etape Poland). Road racing categories, road cornering cues, and road race tactics are irrelevant and actively confusing — this is the most embarrassing possible content bleed for a paying MTB customer.

### 8. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the athlete is tagged as 'mtb' but the UCI Gran Fondo Loutraki is a road gran fondo. The guide includes a 'Road Skills' and 'Road Race Strategy' section (visible in the table of contents) which is actually appropriate for the event, but the plan metadata/persona is set to MTB. Any MTB-specific content elsewhere in the full document (trail skills, MTB cornering, singletrack technique, etc.) would be wrong. The discipline tag needs to be reconciled: if the event is a road gran fondo, the plan must be road, not MTB.

### 9. [critical] ×1  (road/weekend_warrior)
> A 'Gravel Skills' chapter appears in the table of contents (and presumably in the full guide) for a road-discipline athlete. Gravel cornering, surface-reading, or technical trail skills content is wrong for a road racer and would immediately undermine the athlete's trust in the plan's personalization.

### 10. [critical] ×1  (gravel/time_crunched_parent)
> High-stress protocol is self-contradicting: the Recovery Protocol section says 'reduce volume 20% AND eliminate all Zone 4+ work' during high stress, but the core methodology (G Spot / Read the Room) explicitly builds around threshold-touch and VO2 work. There is no bridging instruction telling the athlete how to reconcile these two directives — a stressed athlete could read this as 'skip all hard sessions for 8 weeks,' gutting the plan.

### 11. [major] ×1  (gravel/weekend_warrior)
> Off-day listing reads 'Sunday, Tuesday, Monday' — three days listed out of order and inconsistently (Sunday appears before Monday), which is confusing and likely a generation artifact. For a 5 hr/week athlete with 4 training days, only 3 days off is correct mathematically, but the ordering error makes it look like a bug.

### 12. [major] ×1  (gravel/weekend_warrior)
> The Zone chart omits the lower power bound for Zone 2 (shows '91-123W' with no % FTP for Zone 1 lower bound shown, and Zone 1 shows '0-90W' but no % FTP columns are filled in for Zone 1 or Zone 2 — inconsistent column population that will confuse the athlete when cross-referencing a head unit.

### 13. [major] ×1  (road/time_crunched_parent)
> Taper Intensity is flagged WARN in preview checks but is not addressed anywhere in the guide text provided. Taper execution is critical for an A-priority race; a known issue with taper intensity must be resolved or at minimum flagged to the athlete with explicit coach guidance before sending.

### 14. [major] ×1  (road/time_crunched_parent)
> 'Road Race Strategy' section is listed in the TOC. A gran fondo is not a road race — it is a mass-participation endurance event. Race strategy content should be gran-fondo-specific (pacing a 99-mile effort, managing climbs, aid stations, fueling on the bike) not criterium or road-race tactical advice. Wrong-discipline content erodes athlete trust.

### 15. [major] ×1  (road/time_crunched_parent)
> Weekly Volume check is flagged WARN and is not resolved in the guide. For a time-crunched parent targeting 8 h/week, a volume warning could mean the plan undershoots or overshoots — either way the athlete deserves transparency. The long-ride peak range cited ('3.1–5.2 hours') should be verified against the 8 h/week budget; a 5.2-hour long ride consumes 65% of the weekly hour target in a single session, which may be fine but should be explicitly acknowledged.

### 16. [major] ×1  (gravel/masters_returner)
> 'Road Skills — Road Race Strategy' section (visible in ToC) is road-racing content served to a gravel athlete. Gravel-specific skills (loose surface cornering, descending on gravel, navigation, terrain management) are absent or unconfirmed.

### 17. [major] ×1  (gravel/masters_returner)
> The guide lists Saturday and Tuesday and Wednesday as off days, giving only 4 training days — but the athlete's 7 h/week target with a Time-Crunched methodology typically implies 4-5 riding days. Three consecutive or near-consecutive off days (Tue/Wed/Sat) is an unusual structure that needs explicit justification in the text; none is provided.

### 18. [major] ×1  (gravel/masters_returner)
> Off day placement has Saturday as a rest day, but the long ride is listed as Sunday — for a Saturday race (October 17 is a Saturday) this means the athlete's weekly rhythm never rehearses a Saturday effort, which is a race-specificity gap that should at minimum be flagged in the guide.

### 19. [major] ×1  (mtb/ambitious_first_timer)
> Zone table is missing the power-watt ranges for Zone 1 (Active Recovery) and Zone 2 (Endurance). The columns show '0-106W' for Z1 and '107-144W' for Z2 in the Power column, but the % FTP and % LTHR cells for both zones appear blank/absent in the rendered table. Riders without a power meter relying solely on % FTP or % LTHR ranges have no reference for the two zones they will spend ~70% of their time in.

### 20. [major] ×1  (mtb/ambitious_first_timer)
> The 'G Spot' zone label (GS) between Tempo and Threshold is non-standard and potentially off-putting or unprofessional to a first-time customer who has no prior coaching relationship — it reads as a template artifact from a different customer tier rather than deliberate coach communication.

### 21. [major] ×1  (mtb/ambitious_first_timer)
> The guide states 'your 6 training days, 2 of which are key sessions' in the Weekly Structure section, but the athlete is on a 7-hour Time-Crunched plan. Six training days is high for a Time-Crunched athlete at 7 h/week — it implies an average of ~70 min/day with almost no genuine rest, which contradicts the methodology's principle of intensity-dense sessions with adequate recovery. This figure should be verified against the actual calendar.

### 22. [major] ×1  (mtb/ambitious_first_timer)
> Weekly Volume check returned WARN. At 10 hours/week target for a 34-year-old with 1 year of experience, the volume may be miscalibrated — either too high (injury/overtraining risk for a first-timer) or inconsistently distributed across weeks. This needs investigation before sending.

### 23. [major] ×1  (mtb/ambitious_first_timer)
> The persona label says '1 Years Riding' but the guide text simultaneously calls the athlete 'Intermediate level.' A first-timer with 1 year of experience should be labeled beginner or novice — calling them Intermediate is inconsistent with the persona and could lead to over-prescription of intensity.

### 24. [major] ×1  (mtb/ambitious_first_timer)
> The post-ride recovery nutrition calls for '31g protein + 78-93g carbs within 30 minutes.' The carb range (78-93g) is oddly wide and suspiciously high for immediate post-ride intake — this looks like a templating artifact where two different formula outputs were concatenated rather than resolved to a single recommended value.

### 25. [major] ×1  (road/weekend_warrior)
> The Zone 1 and Zone 6 rows in the zone chart are missing % FTP and % LTHR values — the columns are blank. Every other zone has these figures. A paying athlete consulting the chart during training will notice the gaps; it looks unfinished.
