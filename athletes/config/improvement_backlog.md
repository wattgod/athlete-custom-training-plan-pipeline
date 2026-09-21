# Improvement backlog — 2026-09-21

**Quality 1.58** · avg coach 5.88/10 · contract pass 100% · load 13.25/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/masters_returner, road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably present in the full document. This is road-racing licensure content with zero relevance to a gravel gran fondo athlete whose goal is simply to finish. It is factually wrong for this discipline and deeply embarrassing to send to a paying customer.

### 2. [critical] ×2  (gravel/masters_returner, gravel/weekend_warrior)
> 'Road Race Strategy' section appears in the table of contents. This is a gravel event; road-racing tactics (pack dynamics, criterium positioning, etc.) do not apply and actively mislead the athlete about the nature of their event.

### 3. [critical] ×1  (gravel/masters_returner)
> Taper Intensity flagged as WARN by the automated preview check. A masters athlete aged 60 is particularly sensitive to arriving at the start line under- or over-tapered; a taper-intensity problem in the final week before an A-priority race is not cosmetic — it could compromise race-day performance and reflects a structural plan defect that must be diagnosed and resolved before sending.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> Road-racing content included for a gravel athlete: the Table of Contents explicitly lists 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section. Neither belongs in a gravel plan — this is the wrong discipline content and would immediately erode athlete trust and coaching credibility.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Fueling section ends mid-sentence with a raw placeholder: '0.3-0.4g protein/kg + 1.0-1.2g carbs' — the carbohydrate figure is cut off and the sentence is incomplete. A paying customer cannot act on this, and it exposes the automated generation pipeline.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> Wrong-discipline content: the Table of Contents and guide body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This athlete is doing a gravel gran fondo, not a road criterium/road race with USAC category progression. These sections are copy-pasted road-racing content and are completely irrelevant — they will confuse and undermine trust.

### 7. [critical] ×1  (road/weekend_warrior)
> Off-day summary in the 'At a Glance' box lists THREE off days (Saturday, Wednesday, Monday) but the plan also states the athlete has 4 training days per week. Three off days in a 7-day week leaves only 4 training days — the arithmetic works but Saturday as an off day contradicts the persona section listing Sunday as the long ride day, leaving only Tuesday, Thursday, and Friday as riding days (3 days), not 4. The off-day list needs to be reconciled precisely.

### 8. [critical] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents (and presumably in the full plan body). This is road-racing/criterium content that has zero relevance to a gran fondo finisher goal. It is the wrong discipline subdomain and will confuse or mislead the athlete.

### 9. [critical] ×1  (road/masters_returner)
> The table of contents and guide body include a 'Category 5 to Category 1 Pathway' section. This athlete's goal is simply to FINISH a gran fondo — a mass-participation endurance event, not a USAC licensed road race. Cat 5–1 upgrade pathways are completely irrelevant and will confuse or mislead this athlete. This content is for the wrong discipline/goal and must be removed.

### 10. [critical] ×1  (road/masters_returner)
> The off-days listed in the 'Your Week at a Glance' box are Thursday, Saturday, and Tuesday — but the same box states Sunday is the long-ride day. If Saturday is an off day, the athlete is riding a multi-hour long ride with no prior day of active preparation, which is a minor structural issue, but more importantly Saturday cannot simultaneously be an off day and a lead-in/support day to Sunday. The three off days should be verified against the actual calendar; listing Saturday as off while Sunday is the long ride day is suspicious and potentially wrong.

### 11. [critical] ×1  (gravel/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is in the table of contents and apparently in the guide body — this is road racing licensure content that is completely irrelevant to a gravel event finisher and would confuse and embarrass us in front of this customer.

### 12. [major] ×2  (road/masters_returner, road/weekend_warrior)
> Long-ride duration range cited in the Weekly Structure section ('2.5–4.2 hours') is unusually wide and the upper bound (4.2 h) should be verified against the per-day duration cap check for a 7 h/week athlete — a 4.2 h single ride would consume 60% of the weekly budget in one session, which is aggressive for a weekend warrior persona and inconsistent with a pyramidal volume distribution across 4 days.

### 13. [major] ×1  (gravel/masters_returner)
> 'Road Skills' section is listed without qualification. For a gravel event this should explicitly cover gravel-specific skills (loose-surface cornering, sand/rock line choice, tubeless flat management, loaded descending) rather than generic or road-specific content. The current label suggests generic/road content was pasted in.

### 14. [major] ×1  (gravel/masters_returner)
> Weekly Volume flagged as WARN and TSS Progression flagged as WARN by the automated preview. Neither warning is explained or resolved in the visible guide text. For a 9 h/week masters returner, a volume or TSS ramp issue could mean either under-preparation for a 99-mile event or an over-reach injury risk — both are unacceptable without review.

### 15. [major] ×1  (gravel/masters_returner)
> The plan_start_date is 2026-09-28 and the race is 2026-11-21 (8 weeks = plan ends on race day, which checks out), but the guide states '61 days from today' as the countdown. This is a templated/stale value that will be wrong when emailed on any date other than the generation date. It should either be removed or dynamically rendered correctly — as written it will confuse the athlete.

### 16. [minor] ×2  (gravel/masters_returner, gravel/weekend_warrior)
> Long ride duration range cited as '3.3–5.5 hours' in the Weekly Structure section. At 9 h/week for a masters athlete, a 5.5-hour long ride represents over 60% of total weekly volume in a single session. This upper bound should be verified against the actual calendar caps (Per-Day Duration Caps: PASS) to ensure it is realistic and not a generic template value.

### 17. [major] ×1  (gravel/time_crunched_parent)
> Off days listed as Wednesday, Monday, AND Saturday for a 4-riding-day week — that is three consecutive or near-consecutive off days (Sat/Sun boundary unclear) while placing the long ride on Sunday. Saturday as an off day immediately before the long ride is fine, but listing Monday as an off day alongside Wednesday and Saturday produces an asymmetric week that is never explained or reconciled with the mid-week interval cadence.

### 18. [major] ×1  (gravel/time_crunched_parent)
> The plan goal is 'podium' at El Tour de Tucson (a mass-participation 100-mile gravel/road event with hundreds of finishers per category) on 6 h/week and 8 weeks. The guide never critically engages with this goal — it simply echoes 'Compete' under Goals. A real coach would either validate the podium goal with context (age group podium? corral? specific category?) or gently reframe expectations. Leaving it unaddressed is a coaching gap that could generate complaints.

### 19. [major] ×1  (gravel/time_crunched_parent)
> The 'Road Skills' section appears in the Table of Contents without a gravel-specific equivalent (e.g., loose-surface cornering, gravel descending, tire pressure management). For a 102-mile gravel race, omitting discipline-specific skills content while retaining a road skills header is both a content gap and a wrong-discipline artifact.

### 20. [major] ×1  (gravel/time_crunched_parent)
> Equipment checklist lists 'road bike, in good working order' as the mandatory training bike. The discipline is gravel; the checklist should specify a gravel bike (or at minimum 'gravel or road bike'). Sending a gravel plan that tells the athlete to ride a road bike is embarrassing.

### 21. [major] ×1  (road/weekend_warrior)
> 'Road Race Strategy' section is included in the Table of Contents. This athlete is riding an L'Étape gran fondo (mass-participation, timed, non-competitive road event), not a road race with tactics, attacks, or field dynamics. Road race strategy content is discipline-adjacent but contextually wrong for a finish-goal gran fondo rider and will confuse or mislead the athlete.

### 22. [major] ×1  (road/weekend_warrior)
> Off days are listed as Saturday, Sunday, AND Tuesday — meaning both weekend days are rest days. For a time-crunched athlete targeting a 78-mile event, the long ride is anchored to Thursday. Losing both weekend days is an unusual and suboptimal structure that conflicts with the typical real-world weekend availability of a self-described 'weekend warrior,' and the plan itself acknowledges the long rides are already shorter than ideal. This needs a clear rationale or correction.

### 23. [major] ×1  (road/weekend_warrior)
> The 'Women-Specific Considerations' section is listed in the table of contents but the truncated text does not reveal its content. Given the athlete is female (44 years old, peri/post-menopausal range), this section must be substantive and accurate — if it is boilerplate or empty it is a significant gap for this demographic.

### 24. [major] ×1  (road/masters_returner)
> The TSS Progression check flagged WARN in the automated preview and was never resolved or acknowledged. A WARN on TSS progression for a 57-year-old masters returner is clinically significant — excessive TSS ramp rate is a primary injury and overtraining risk for this persona. The guide should not be sent until the underlying calendar is confirmed safe or the guide text explicitly addresses the managed ramp.

### 25. [major] ×1  (road/masters_returner)
> The fueling section prescribes 60g carbs/hour with an implied race duration of ~6h41m (from the JSON duration field), but the guide text never states the expected race duration or total carbohydrate target for the athlete. For a 99-mile gran fondo at masters pace this duration is plausible, but omitting it means the athlete has no anchor for their race-day nutrition plan — a significant gap for a goal of 'finish' on a long event.
